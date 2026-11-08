(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x77 ((_ extract 2 2) i_4)))
 (let ((?x2380 ((_ extract 1 0) i_4)))
 (let ((?x28 (concat ?x2380 ?x77)))
 (let ((?x531 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x2246 (ite (and (distinct ?x531 ?x28) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x2246 (_ bv1 1)))))))))
(assert
 (let (($x806 (= i_4 (_ bv0 3))))
(not $x806)))
(check-sat)
