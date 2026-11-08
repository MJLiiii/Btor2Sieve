(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x21 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x570 (bvor (bvlshr i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x2085 (ite (and (distinct ?x570 ?x21) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x2085 (_ bv1 1)))))))
(assert
 (let ((?x570 (bvor (bvlshr i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
(let (($x2531 (and (distinct ?x570 (_ bv4 3)) true)))
(not $x2531))))
(check-sat)
