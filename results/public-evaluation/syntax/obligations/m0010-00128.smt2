(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x560 (and (distinct i_7 (_ bv255 8)) true)))
(not $x560)))
(check-sat)
