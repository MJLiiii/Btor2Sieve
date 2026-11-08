(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x49 ((_ extract 2 2) i_4)))
 (let ((?x30 ((_ extract 1 0) i_4)))
 (let ((?x42 (concat ?x30 ?x49)))
 (let ((?x159 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x193 (ite (and (distinct ?x159 ?x42) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x193 (_ bv1 1)))))))))
(assert
 (let ((?x30 ((_ extract 1 0) i_4)))
(let (($x73 (bvsle ?x30 (_ bv0 2))))
(not $x73))))
(check-sat)
