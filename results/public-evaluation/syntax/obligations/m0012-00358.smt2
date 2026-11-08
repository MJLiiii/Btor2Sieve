(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x738 (bvor (bvlshr i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
 (let ((?x6 (ite (and (distinct ?x738 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x6 (_ bv1 1))))))
(assert
 (let ((?x738 (bvor (bvlshr i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
(let (($x383 (and (distinct ?x738 (_ bv1 3)) true)))
(not $x383))))
(check-sat)
