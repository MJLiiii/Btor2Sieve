(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x54 (bvor (bvlshr i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
 (let ((?x2153 (ite (and (distinct ?x54 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x2153 (_ bv1 1))))))
(assert
 (let (($x7153 (bvsge i_4 (_ bv1 3))))
(not $x7153)))
(check-sat)
