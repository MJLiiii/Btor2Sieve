(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x246 ((_ extract 2 2) i_4)))
 (let ((?x726 ((_ extract 1 0) i_4)))
 (let ((?x505 (concat ?x726 ?x246)))
 (let ((?x21 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x1042 (ite (and (distinct ?x21 ?x505) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x1042 (_ bv1 1)))))))))
(assert
 (let ((?x726 ((_ extract 1 0) i_4)))
(let (($x221 (= ?x726 (_ bv0 2))))
(not $x221))))
(check-sat)
